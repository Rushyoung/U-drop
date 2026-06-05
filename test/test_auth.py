from client import UdropClient
import time
import random

def run_auth_tests():
    client = UdropClient()
    
    # 场景 1: 固定账号
    print("\n=== [Auth] 测试固定账号 ===")
    fixed_acc = "persistent_tester"
    client.register(fixed_acc, "password123", "fixed_device_001")
    client.login(fixed_acc, "password123", "fixed_device_001")

    # 场景 2: 随机账号 (模拟新用户)
    print("\n=== [Auth] 测试随机账号 ===")
    random_acc = f"user_{int(time.time())}_{random.randint(100,999)}"
    client.register(random_acc, "password123", "rand_device_001")
    client.login(random_acc, "password123", "rand_device_001")

if __name__ == "__main__":
    run_auth_tests()
