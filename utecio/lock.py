import asyncio

from __init__ import logger
from device import UtecBleDevice, BleResponse, BleRequest
from enums import BleResponseCode, BLECommandCode, ServiceUUID
from constants import BATTERY_LEVEL, LOCK_MODE, LOCK_STATUS

class UtecBleLock(UtecBleDevice):
    def __init__(self, device_name: str, uid: str, password: str, mac_address: str, max_retries: float = 3, retry_delay: float = 0.5, bleakdevice_callback: callable = None):
        super().__init__(device_name, mac_address, max_retries, retry_delay, bleakdevice_callback)
        self.uid = uid
        self.password = password
        self.response = BleResponse(bytearray(0))
        self.lock_status = -1
        self.bolt_status = -1
        self.battery = -1
        self.work_mode = -1
        self.mute = False
        self.sn = None

    async def unlock(self):
        try:
            await self.send_encrypted(BleRequest(BLECommandCode.UNLOCK, self.uid, self.password))
            logger.info("Unlock command sent successfully.")
        except Exception as e:
            logger.error(f"Error while sending unlock command: {e}")
    
    async def update(self):
        try:
            await self.start_notify(ServiceUUID.DATA.value, self.__receive_write_response)
            await self.send_encrypted(BleRequest(BLECommandCode.GET_LOCK_STATUS))
            await self.send_encrypted(BleRequest(BLECommandCode.GET_BATTERY))
            await self.send_encrypted(BleRequest(BLECommandCode.GET_SN, None, None, bytearray([16])))
            await self.send_encrypted(BleRequest(BLECommandCode.GET_MUTE))
            await asyncio.sleep(2)
            await self.stop_notify(ServiceUUID.DATA.value)
            logger.info("Update process completed.")
        except Exception as e:
            logger.error(f"Error during update: {e}")
            
        # return await super().update()

    async def _update_lock(self, response: BleResponse):
        try:
            logger.debug(f"Response {response.command.name}: {response.package.hex()}")
            if response.command == BleResponseCode.LOCK_STATUS:
                self.lock_status = int(response.data[1])
                self.bolt_status = int(response.data[2])
                logger.debug(f"lock:{self.lock_status}, {LOCK_MODE[self.lock_status]} |  bolt:{self.bolt_status}, {LOCK_STATUS[self.bolt_status]}")
            elif response.command == BleResponseCode.BATTERY:
                self.battery = int(response.data[1])
                logger.debug(f"power level:{self.battery}, {BATTERY_LEVEL[self.battery]}")
            elif response.command == BleResponseCode.SN:
                self.sn = response.data.decode('ISO8859-1')
                logger.debug(f"serial:{self.sn}")
            elif response.command == BleResponseCode.MUTE:
                self.mute = bool(response.data[1])
                logger.debug(f"sound:{self.mute}")
        except Exception as e:
            logger.error(f"Error while updating data from response: {e}")

    async def __receive_write_response(self, sender: int, data: bytearray):
        try:
            self.response.append(data, self.secret_key.aes_key)
            if self.response.completed:
                if self.response.is_valid:
                    await self._update_lock(self.response)
                self.response.reset()
        except Exception as e:
            logger.error(f"Error while receiving write response: {e}")
