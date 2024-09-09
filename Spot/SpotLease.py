from bosdyn.client.lease import ResourceAlreadyClaimedError, LeaseKeepAlive


class SpotLease:
    """
    Spot 로봇의 제어권을 관리하고 제어하기 위한 클래스입니다.
    이 객체를 통해 Lease를 획득하거나 반환할 수 있습니다.
    """
    def __init__(self, client):
        self.lease_client = client
        self.lease = None
        self.lease_keepalive = None

    def toggle_lease(self):
        """
        Lease를 토글하는 메소드입니다. Lease가 활성화되어 있을 경우 반환하고, 비활성화되어 있을 경우 시작합니다.

        Returns:
            bool: Lease 상태 (True: 활성화, False: 비활성화)
        """
        if self.lease_keepalive is None:
            return self.start_lease()
        else:
            return self.return_lease()

    def start_lease(self):
        """
        Lease를 시작하는 메소드입니다.

        Returns:
            bool: Lease 시작 여부
        """
        try:
            print("Lease Acquire")
            self.lease = self.lease_client.acquire()
        except ResourceAlreadyClaimedError as err:
            print("The robot's lease is currently in use. Check for a tablet connection or try again in a few seconds.")
            self.lease = self.lease_client.take()

        self.lease_keepalive = LeaseKeepAlive(self.lease_client, must_acquire=True, return_at_exit=True)
        return True

    def return_lease(self):
        """
        Lease를 반환하는 메소드입니다.

        Returns:
            bool: Lease 반환 여부
        """
        try:
            self.lease_keepalive.shutdown()
        except RuntimeError:
            print("다른 기기에서 Lease를 가져갔습니다.")

        self.lease_keepalive = None
        self.lease = None

        return True
