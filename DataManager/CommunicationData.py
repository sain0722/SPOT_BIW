from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TagInfo:
    type: str
    scope: str
    name: str
    description: str
    datatype: str
    specifier: str

class TagManager:
    def __init__(self):
        self.send_tags = self.load_send_tags()
        self.receive_tags = self.load_receive_tags()

    def load_send_tags(self) -> List[TagInfo]:
        # 미리 정의된 send 예제 데이터
        return [
            TagInfo('ALIAS', 'S600_RB1_I', None, None, None, 'Local:10:I.Data[10]'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_HOME_POSI', '도크에 앉아있는 상태', '', '', 'Local:10:I.Data[10].00'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_LAST_WORK_COMP', '최종 작업완료', '', '', 'Local:10:I.Data[10].01'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_1ST_WORK_COMP', 'Fender QR코드 촬영', '', '', 'Local:10:I.Data[10].02'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_2ND_WORK_COMP', 'RR DR Hole 촬영(2군데)', '', '', 'Local:10:I.Data[10].03'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_3RD_WORK_COMP', 'Side OTR QR코드 촬영', '', '', 'Local:10:I.Data[10].04'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_AUTORUNNING', 'SPOT POWER+MOTER ON', '', '', 'Local:10:I.Data[10].05'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_BATTERY_LOW', 'WARNING', '', '', 'Local:10:I.Data[10].06'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_TOTAL_ERR', '종합 이상', '', '', 'Local:10:I.Data[10].07'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_EM_STOP', '비상정지', '', '', 'Local:10:I.Data[10].08'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_NON_INT', 'AGV 간섭무', '', '', 'Local:10:I.Data[10].09'),
            TagInfo('ALIAS', '', '', '', '', 'Local:10:I.Data[10].10'),
            TagInfo('ALIAS', '', '', '', '', 'Local:10:I.Data[10].11'),
            TagInfo('ALIAS', '', '', '', '', 'Local:10:I.Data[10].12'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_WORK_COMP_RESET', '작업완료 신호 초기화(AGV OUT 신호받을 시)', '', '', 'Local:10:I.Data[10].13'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_BYPASS_ON', 'BATTERY_LOW 시 검사 없이 도크에 앉아있기', '', '', 'Local:10:I.Data[10].14'),
            TagInfo('ALIAS', 'S600_SPOT_RB1_I_HEART_BIT', '통신체크용 0.5초 플리커', '', '', 'Local:10:I.Data[10].15')
        ]

    def load_receive_tags(self) -> List[TagInfo]:
        # 미리 정의된 receive 예제 데이터
        return [
            TagInfo('ALIAS', 'S600_SPOT_RB1O', '', '', '', 'Local:10:O.Data[10]'),
            TagInfo('ALIAS', 'S600_AGV_O_AUTORUNNING', 'AGV 상태', '', '', 'Local:10:O.Data[10].00'),
            TagInfo('ALIAS', 'S600_AGV_O_WANRNING', '정위치 주변 구역에서 AGV 경고 (배터리 경고 등)', '', '', 'Local:10:O.Data[10].01'),
            TagInfo('ALIAS', 'S600_AGV_O_FAULT', '정위치 주변 구역에서 AGV 이상', '', '', 'Local:10:O.Data[10].02'),
            TagInfo('ALIAS', 'S600_AGV_O_EM_STOP', '비상정지', '', '', 'Local:10:O.Data[10].03'),
            TagInfo('ALIAS', '', '', '', '', 'Local:10:O.Data[10].04'),
            TagInfo('ALIAS', 'S600_AGV_O_PART_OK', 'AGV에 검사대상바디 있음', '', '', 'Local:10:O.Data[10].05'),
            TagInfo('ALIAS', 'S600_AGV_O_PART_NONE', 'AGV에 검사대상바디 없음', '', '', 'Local:10:O.Data[10].06'),
            TagInfo('ALIAS', 'S600_AGV_O_POS_OK', 'AGV 정위치 상태', '', '', 'Local:10:O.Data[10].07'),
            TagInfo('ALIAS', 'S600_AGV_O_NON_INT', 'AGV 간섭무 상태', '', '', 'Local:10:O.Data[10].08'),
            TagInfo('ALIAS', 'S600_AGV_O_BODYTYPE_ON', 'AGV에 차종 있음', '', '', 'Local:10:O.Data[10].09'),
            TagInfo('ALIAS', 'S600_AGV_O_BODYTYPE_NONE', 'AGV에 차종 없음', '', '', 'Local:10:O.Data[10].10'),
            TagInfo('ALIAS', 'S600_AGV_O_IN_RUNNING', 'AGV에 검사공정으로 진입', '', '', 'Local:10:O.Data[10].11'),
            TagInfo('ALIAS', 'S600_AGV_O_OUT_RUNNING', 'AGV에 검사공정 밖으로 진출', '', '', 'Local:10:O.Data[10].12'),
            TagInfo('ALIAS', '', '', '', '', 'Local:10:O.Data[10].13'),
            TagInfo('ALIAS', '', '', '', '', 'Local:10:O.Data[10].14'),
            TagInfo('ALIAS', 'S600_AGV_O_HEART_BIT', '통신체크용 0.5초 플리커', '', '', 'Local:10:O.Data[10].15')
        ]

    def get_send_tag_info(self, scope: str) -> Optional[TagInfo]:
        for tag in self.send_tags:
            if tag.scope == scope:
                return tag
        return None

    def get_receive_tag_info(self, scope: str) -> Optional[TagInfo]:
        for tag in self.receive_tags:
            if tag.scope == scope:
                return tag
        return None

    def update_send_tag_info(self, scope: str, name: Optional[str] = None, description: Optional[str] = None):
        tag = self.get_send_tag_info(scope)
        if tag:
            if name is not None:
                tag.name = name
            if description is not None:
                tag.description = description

    def update_receive_tag_info(self, scope: str, name: Optional[str] = None, description: Optional[str] = None):
        tag = self.get_receive_tag_info(scope)
        if tag:
            if name is not None:
                tag.name = name
            if description is not None:
                tag.description = description

    def add_send_tag_info(self, tag: TagInfo):
        self.send_tags.append(tag)

    def add_receive_tag_info(self, tag: TagInfo):
        self.receive_tags.append(tag)

    def save_send_tags_to_file(self, file_path: str):
        with open(file_path, 'w', encoding='utf-8') as f:
            for tag in self.send_tags:
                f.write(f"{tag.type},{tag.scope},{tag.name},{tag.description},{tag.datatype},{tag.specifier}\n")

    def save_receive_tags_to_file(self, file_path: str):
        with open(file_path, 'w', encoding='utf-8') as f:
            for tag in self.receive_tags:
                f.write(f"{tag.type},{tag.scope},{tag.name},{tag.description},{tag.datatype},{tag.specifier}\n")

    def load_send_tags_from_file(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                type, scope, name, description, datatype, specifier = line.strip().split(',')
                tag = TagInfo(type, scope, name, description, datatype, specifier)
                self.add_send_tag_info(tag)

    def load_receive_tags_from_file(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                type, scope, name, description, datatype, specifier = line.strip().split(',')
                tag = TagInfo(type, scope, name, description, datatype, specifier)
                self.add_receive_tag_info(tag)


if __name__ == "__main__":
    tag_manager = TagManager()

    # send 태그 데이터 출력
    print("Send Tags:")
    for tag in tag_manager.send_tags:
        print(tag)

    # receive 태그 데이터 출력
    print("\nReceive Tags:")
    for tag in tag_manager.receive_tags:
        print(tag)

    # 특정 send 태그 정보 가져오기
    send_tag_info = tag_manager.get_send_tag_info('S600_SPOT_RB1_I_HOME_POSI')
    print("\nSend Tag Info:", send_tag_info)

    # 특정 receive 태그 정보 가져오기
    receive_tag_info = tag_manager.get_receive_tag_info('S600_AGV_O_AUTORUNNING')
    print("\nReceive Tag Info:", receive_tag_info)

    # send 태그 정보 업데이트
    tag_manager.update_send_tag_info('S600_SPOT_RB1_I_HOME_POSI', description='Updated Description')

    # receive 태그 정보 업데이트
    tag_manager.update_receive_tag_info('S600_AGV_O_AUTORUNNING', description='Updated Description')

    # 업데이트된 send 태그 정보 출력
    updated_send_tag_info = tag_manager.get_send_tag_info('S600_SPOT_RB1_I_HOME_POSI')
    print("\nUpdated Send Tag Info:", updated_send_tag_info)

    # 업데이트된 receive 태그 정보 출력
    updated_receive_tag_info = tag_manager.get_receive_tag_info('S600_AGV_O_AUTORUNNING')
    print("\nUpdated Receive Tag Info:", updated_receive_tag_info)

    # send 태그 정보 파일로 저장
    tag_manager.save_send_tags_to_file('send_tags.csv')

    # receive 태그 정보 파일로 저장
    tag_manager.save_receive_tags_to_file('receive_tags.csv')

    # 파일에서 send 태그 정보 로드
    new_tag_manager = TagManager()
    new_tag_manager.load_send_tags_from_file('send_tags.csv')
    print("\nLoaded Send Tags from File:")
    for tag in new_tag_manager.send_tags:
        print(tag)

    # 파일에서 receive 태그 정보 로드
    new_tag_manager.load_receive_tags_from_file('receive_tags.csv')
    print("\nLoaded Receive Tags from File:")
    for tag in new_tag_manager.receive_tags:
        print(tag)
