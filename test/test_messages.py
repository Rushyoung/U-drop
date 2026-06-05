from client import UdropClient

def run_timeline_tests():
    client = UdropClient()
    acc = "persistent_tester"
    client.login(acc, "password123", "fixed_device_001")

    # 1. 拉取 Initial
    res = client.get_messages(mode="initial", limit=3)
    data = res.json()["data"]
    if not data: return

    # 2. 拉取 Before
    oldest_id = data[-1]["id"]
    client.get_messages(mode="before", anchor_id=oldest_id, limit=2)

    # 3. 拉取 After
    newest_id = data[0]["id"]
    client.create_message(content="Testing After mode...")
    client.get_messages(mode="after", anchor_id=newest_id, limit=5)

if __name__ == "__main__":
    run_timeline_tests()
