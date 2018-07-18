import json
from queue import Queue

import server_manager
import server_module_handler as mh
import server_packet
from log import log


class ModuleManager(server_manager.Manager):

    def __init__(self, clnthndlr):
        self.clnthndlr = clnthndlr
        self.requests_queue = Queue()
        self.module = None

    def _export_module_data(self, module_data):
        pk = server_packet.Packet(module_data, server_packet.PACKET_ID_FUNC_INIT)
        self.clnthndlr.send_packet(pk)

    def _func_call_return_value(self, return_data):
        pk = server_packet.Packet(str(return_data), server_packet.PACKET_ID_FUNC_CALL_RETURN)
        self.clnthndlr.send_packet(pk)

    def _func_call_return_error(self, error_info):
        pk = server_packet.Packet((str(dict(data=error_info))), server_packet.PACKET_ID_FUNC_CALL_ERROR)
        self.clnthndlr.send_packet(pk)

    def handle_request(self, clnthndlr, packet_id, data):
        try:
            if packet_id is server_packet.PACKET_ID_FUNC_INIT:
                # Module Handler
                formatted_modue_export = mh.format_module_export(self.module)
                self.requests_queue.put((packet_id, formatted_modue_export))
            elif packet_id is server_packet.PACKET_ID_FUNC_CALL:
                data = json.loads(data.get_data())

                host_cls = data["host_cls"]
                func_type = int(data["func_type"])
                func_name = data["name"]
                func_args = list(data["args"])

                result = None

                if func_type == mh.FUNC_TYPE.MODULE_FUNC.value:
                    result = mh.exec_func(self.module, func_name, *func_args)
                elif func_type == mh.FUNC_TYPE.INSTANCE_FUNC.value:
                    # TODO resolve instance methods
                    # cls_instance = cls()
                    # method = getattr(cls_instance, func_name)
                    # result = method(*func_args)
                    result = "INSTANCE_METHODS ARE NOT SUPPORTED ATM"
                elif func_type == mh.FUNC_TYPE.CLASS_FUNC.value:
                    cls = mh.get_class(self.module, host_cls)
                    result = mh.exec_func(cls, func_name, *func_args)
                elif func_type == mh.FUNC_TYPE.PROPERTY_FUNC.value:
                    # TODO resolve property methods
                    result = "PROPERTY_METHODS ARE NOT SUPPORTED ATM"
                elif func_type == mh.FUNC_TYPE.STATIC_FUNC.value:
                    cls = mh.get_class(self.module, host_cls)
                    result = mh.exec_func(cls, func_name, *func_args)

                    # TODO remove redundant encoding/decoding
                    self.requests_queue.put((packet_id, result))
        except Exception as e:
            log(e)
            self._func_call_return_error(str(e))
            raise e

    def init(self):
        self.module = mh.load_module("secretmath")

    def loop(self):
        if not self.module:
            log("Module not initialized")
            return

        if not self.requests_queue.empty():
            (packet_ID, result) = self.requests_queue.get()

            if packet_ID is server_packet.PACKET_ID_FUNC_INIT:
                self._export_module_data(result)
            elif packet_ID is server_packet.PACKET_ID_FUNC_CALL:
                self._func_call_return_value(result)

    def responds_to(self, packet_id):
        return 0 <= packet_id < 100