import time
from datetime import datetime
from concurrent.futures import CancelledError

from PySide6.QtCore import QObject, Signal, QTimer, QThread
from opcua import Client, ua

import DefineGlobal


class BIWOPCUAClient(QObject):
    data_changed = Signal(str, ua.Variant)
    received_spec_data = Signal(str)
    received_agv_signal = Signal(bool)
    received_agv_no = Signal(str)

    def __init__(self, server_url):
        super().__init__()
        self.server_url = server_url
        self.client = Client(server_url)
        self.client.session_timeout = 600000

        self.subscription = None
        self.handler = None

        self.connected = False

        self.tag_map = {}  # NodeId와 태그 이름의 매핑을 저장
        self.timer = QTimer()

        self.thread_receive_data = DataReceiveWorker(self.read_node_id)
        self.thread_receive_data.received_agv_signal.connect(self.received_agv_signal)
        self.thread_receive_data.received_spec_data.connect(self.received_spec_data)
        self.thread_receive_data.received_agv_no.connect(self.received_agv_no)

    def opc_connect(self):
        try:
            self.client.connect()
            self.thread_receive_data.start()
            # self.create_subscription()
            print(f"Connected to OPC UA server at {self.server_url}")
            self.connected = True
        except Exception as e:
            print(f"Failed to connect to OPC UA server: {e}")

    def disconnect(self):
        try:
            if self.connected:
                if self.subscription:
                    self.subscription.delete()
                self.client.disconnect()
                self.thread_receive_data.stop()
                self.connected = False
                print(f"Disconnected from OPC UA server at {self.client.server_url}")
            else:
                print("Client is not connected, no need to disconnect.")
        except Exception as e:
            print(f"An error occurred during disconnect: {e}")

    def is_connected(self, connected):
        self.connected = connected

    def attempt_reconnect(self):
        print("Attempting to reconnect to OPC UA server...")
        self.opc_connect()
        if self.connected:
            print("Reconnected!")

    def read_tag(self, tag):
        try:
            # ns = 2  # 네임스페이스 인덱스
            # node_id = list(self.tag_map.values()).index(tag) + 1  # 태그 이름을 인덱스로 변환하여 NodeId를 찾음
            # node = self.client.get_node(f"ns={ns};i={node_id}")
            # value = node.get_value()

            value = "TEST VALUE"
            # print(f"Read value {value} from tag {tag}")
            return value
        except WindowsError as win_ex:
            print(win_ex)
            # self.attempt_reconnect()
            return None

        except Exception as e:
            print(f"Failed to read value from tag {tag}: {e}")
            # self.attempt_reconnect()
            return None

    def read_node_id(self, node_id):
        try:
            ns = 2
            node = self.client.get_node(f"ns={ns};s={node_id}")
            value = node.get_value()
            # print(f"Read value {value} from tag {node_id}")
            return value
        except WindowsError as win_ex:
            print(win_ex)
            # self.attempt_reconnect()
            return None

        except Exception as e:
            print(f"[opc_client.py - read_node_id] Failed to read value from node_id {node_id}: {e}")
            # self.attempt_reconnect()
            return None

    def write_tag(self, tag, value):
        try:
            ns = 2  # 네임스페이스 인덱스
            node_id = list(self.tag_map.values()).index(tag) + 1  # 태그 이름을 인덱스로 변환하여 NodeId를 찾음
            node = self.client.get_node(f"ns={ns};i={node_id}")
            node.set_value(ua.Variant(value, ua.VariantType.Int32))
            print(f"Written value {value} to tag {tag} (NodeId: ns={ns};i={node_id})")
        except Exception as e:
            print(f"Failed to write value {value} to tag {tag}: {e}")

    def write_node_id(self, node_id, value):
        try:
            ns = 2  # 네임스페이스 인덱스
            node = self.client.get_node(f"ns={ns};s={node_id}")
            value_type = type(value)
            if value_type == int:
                variant = ua.Variant(value, ua.VariantType.Int32)
            elif value_type == bool:
                variant = ua.Variant(value, ua.VariantType.Boolean)
            elif value_type == str:
                variant = ua.Variant(value, ua.VariantType.String)
            else:
                print(f"Unsupported value type: {value_type}")
                return

            node.set_value(ua.DataValue(variant))
            # print(f"[{datetime.now()}] [opc_clint] Written value {value} to tag {node_id} (NodeId: ns={ns};i={node_id})")
            return True

        except Exception as e:
            print(f"Failed to write value {value} to tag {node_id}: {e}")
            return False

    def get_root_node(self):
        return self.client.get_root_node()

    def get_objects_node(self):
        return self.client.get_objects_node()

    # def subscribe_to_nodes(self, node_ids, interval=1000):
    #     try:
    #         self.handler = SubHandler()
    #         self.subscription = self.client.create_subscription(interval, self.handler)
    #         handles = []
    #         for node_id in node_ids:
    #             node = self.client.get_node(node_id)
    #             handle = self.subscription.subscribe_data_change(node)
    #             handles.append(handle)
    #             print(f"Subscribed to node {node_id} with handle {handle}")
    #         return handles
    #     except Exception as e:
    #         print(f"Failed to subscribe to nodes {node_ids}: {e}")
    #         return []

    def create_subscription(self):
        handler = SubHandler(self)
        self.subscription = self.client.create_subscription(100, handler)
        ns = 2  # 네임스페이스 인덱스

        node_POS_OK          = self.client.get_node(f"ns={ns};s={DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_POS_OK}")
        node_PART_OK         = self.client.get_node(f"ns={ns};s={DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_PART_OK}")
        node_BODYTYPE_ON     = self.client.get_node(f"ns={ns};s={DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_BODYTYPE_ON}")
        node_BODYTYPE_NONE   = self.client.get_node(f"ns={ns};s={DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_BODYTYPE_NONE}")
        node_AUTORUNNING     = self.client.get_node(f"ns={ns};s={DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_AUTORUNNING}")
        node_test            = self.client.get_node(f"ns={ns};s={DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON}")

        self.subscription.subscribe_data_change(node_POS_OK)
        self.subscription.subscribe_data_change(node_PART_OK)
        self.subscription.subscribe_data_change(node_BODYTYPE_ON)
        self.subscription.subscribe_data_change(node_BODYTYPE_NONE)
        self.subscription.subscribe_data_change(node_AUTORUNNING)
        self.subscription.subscribe_data_change(node_test)

        # for idx in range(len(self.tags)):
        #     node = self.client.get_node(f"ns={ns};s={i}")
        #     self.tag_map[node.nodeid] = self.tags[idx]  # NodeId와 태그 이름을 매핑
        #     self.subscription.subscribe_data_change(node)

    def unsubscribe(self):
        if self.subscription:
            self.subscription.delete()
            print("Unsubscribed from all nodes")

    # 전체 노드 출력
    def browse_node(self, node_id):
        try:
            node = self.client.get_node(node_id)
            children = node.get_children()
            print(f"Node {node_id} children:")
            for child in children:
                print(f" - {child}: {child.get_browse_name()}")
                self.browse_node(child.nodeid)
        except Exception as e:
            self.connected = False
            print(f"Failed to browse node {node_id}: {e}")

    # 노드의 위치를 알 경우, 정확한 경로로 노드에 접근
    # ex. ns=2;s=S600_SPOT_RB1_I_HOME_POSI
    def get_node_by_path(self, path):
        """
        주어진 경로를 사용하여 노드에 접근합니다.
        """
        try:
            node = self.client.get_node(path)
            return node
        except Exception as e:
            print(f"Failed to get node by path {path}: {e}")
            return None

    def browse_and_find_node(self, root_node, tag_name):
        """
        선택적으로 노드 트리를 탐색하여 태그 이름에 해당하는 노드를 찾습니다.
        """
        try:
            # Objects 노드를 가져옵니다.
            objects_node = root_node.get_child(["0:Objects"])

            # Objects 노드 아래의 자식 노드를 순회합니다.
            for node in objects_node.get_children():
                browse_name = node.get_browse_name()
                if browse_name.Name == tag_name:
                    return node
                # 자식 노드가 더 있다면, 해당 노드에서 다시 탐색합니다.
                child_result = self.browse_and_find_node_recursive(node, tag_name)
                if child_result:
                    return child_result
        except Exception as e:
            print(f"Failed to browse node {root_node}: {e}")
        return None

    def browse_and_find_node_recursive(self, node, tag_name):
        """
        재귀적으로 노드 트리를 탐색하여 태그 이름에 해당하는 노드를 찾습니다.
        """
        try:
            for child in node.get_children():
                browse_name = child.get_browse_name()
                if browse_name.Name == tag_name:
                    return child
                result = self.browse_and_find_node_recursive(child, tag_name)
                if result:
                    return result
        except Exception as e:
            print(f"Failed to browse node {node}: {e}")
        return None

    def send_complete_signal(self):
        # execute after 30s later.
        # st_time = time.time()
        # while st_time + 21 > time.time():
        #     print("wait")
        #     time.sleep(1)

        rb1_node_id = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP
        rb2_node_id = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP

        print(f"[{datetime.now()}]Try write {rb1_node_id}")
        self.write_node_id(rb1_node_id, True)

        print(f"[{datetime.now()}]Try write {rb2_node_id}")

        tag_name = "S600_SPOT_RB2_I_LAST_WORK_COMP"
        tag_full_name = "[MF]" + tag_name
        value = True
        # self.write_node_id(rb2_node_id, True)
        self.write_node_id(tag_full_name, value)

    def reset_signals(self):
        rb1_node_id = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP
        rb2_node_id = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP

        self.write_node_id(rb1_node_id, False)

        tag_name = "S600_SPOT_RB2_I_LAST_WORK_COMP"
        tag_full_name = "[MF]" + tag_name
        value = True
        # self.write_node_id(rb2_node_id, True)
        self.write_node_id(tag_full_name, value)

        # self.write_node_id(rb2_node_id, False)

class SubHandler:
    def __init__(self, client):
        self.client = client

    def datachange_notification(self, node, val, data):
        current_time = datetime.now()
        print(f"[{current_time}] Data change on node {node}: {val}")
        tag = self.client.tag_map.get(node.nodeid, "Unknown")
        self.client.data_changed.emit(tag, val)
        if str(node) == "ns=2;s=[MF]S600_AGV_I_POS_OK":
            if val:
                print("[OPC DATA CHANGE] SEND COMPLETE SIGNAL")
                # self.client.send_complete_signal()
            else:
                print("[OPC DATA CHANGE] RESET SIGNALS")
                self.client.reset_signals()

        if str(node) == "ns=2;s=[MF]S600_AGV_I_Workcompl_Feedback":
            self.client.reset_signals()


class DataReceiveWorker(QThread):
    received_spec_data  = Signal(str)
    received_agv_signal = Signal(bool)
    received_agv_no = Signal(str)

    def __init__(self, function):
        super().__init__()
        self.read_node_id_function = function
        self.is_running = True

    def run(self):
        while self.is_running:
            if not DefineGlobal.PROCESS_THREAD_IS_RUNNING:
                time.sleep(.5)
                continue

            spec_data = self.read_node_id_function(DefineGlobal.OPC_SPOT_AGV_BT_Data.S600_SPOT_AGV_BT_Data_SPEC)
            agv_signal = self.read_node_id_function(DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_POS_OK)
            agv_no = self.read_node_id_function(DefineGlobal.OPC_AGV_I_TAG.AGV_Position_72180_AGV_NO)

            self.received_spec_data.emit(spec_data)
            self.received_agv_signal.emit(agv_signal)
            self.received_agv_no.emit(str(agv_no))
            time.sleep(.1)

    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()

