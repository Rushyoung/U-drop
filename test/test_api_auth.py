import requests
import time
import statistics
import concurrent.futures

# 假设服务器运行在 http://127.0.0.1:8000
BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
NUM_USERS = 50
WORKERS = 10 # 并发线程数

def do_register(user_idx):
    """模拟一个设备发起注册请求"""
    account = f"perf_user_{user_idx}_{int(time.time())}"
    password = f"perf_pass_{user_idx}"
    payload = {
        "account": account,
        "password": password,
        "device_id": f"dev_{user_idx}_0",
        "device_type": 0, # 例如 0 代表 Web
        "device_name": f"Web Device {user_idx}",
        "expire_time": 3600
    }
    
    t0 = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/register", json=payload)
        t1 = time.time()
        return ("register", user_idx, resp.status_code, t1 - t0, account, password)
    except Exception as e:
        return ("register", user_idx, 0, 0, account, password)

def do_login(user_idx, account, password):
    """模拟同一个用户的第二台设备发起登录请求"""
    payload = {
        "account": account,
        "password": password,
        "device_id": f"dev_{user_idx}_1",
        "device_type": 1, # 例如 1 代表 Android
        "device_name": f"Android Device {user_idx}",
        "expire_time": 3600
    }
    
    t0 = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/login", json=payload)
        t1 = time.time()
        return ("login", user_idx, resp.status_code, t1 - t0)
    except Exception as e:
        return ("login", user_idx, 0, 0)

def test_perf():
    print(f"🚀 开始性能与并发测试")
    print(f"目标: {NUM_USERS} 个用户，每个用户 2 台设备 (共 {NUM_USERS * 2} 台设备)")
    print(f"并发线程数: {WORKERS}")
    
    register_times = []
    login_times = []
    failed_regs = 0
    failed_logins = 0

    registered_users = []

    start_total = time.time()

    # ---------------------------------------------------------
    # 阶段 1：并发注册 50 个用户 (首设备)
    # ---------------------------------------------------------
    print(f"\n[阶段 1] 正在并发注册 {NUM_USERS} 个用户...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(do_register, i) for i in range(NUM_USERS)]
        for future in concurrent.futures.as_completed(futures):
            op, idx, status, duration, acc, pwd = future.result()
            if status == 200:
                register_times.append(duration)
                registered_users.append((idx, acc, pwd))
            else:
                failed_regs += 1
                print(f"⚠️ 用户 {idx} 注册失败, 状态码: {status}")

    # ---------------------------------------------------------
    # 阶段 2：并发登录另外 50 台设备 (次设备)
    # ---------------------------------------------------------
    print(f"\n[阶段 2] 正在并发登录第二台设备 ({len(registered_users)} 台)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(do_login, idx, acc, pwd) for idx, acc, pwd in registered_users]
        for future in concurrent.futures.as_completed(futures):
            op, idx, status, duration = future.result()
            if status == 200:
                login_times.append(duration)
            else:
                failed_logins += 1
                print(f"⚠️ 用户 {idx} 登录失败, 状态码: {status}")

    end_total = time.time()

    # ---------------------------------------------------------
    # 输出报告
    # ---------------------------------------------------------
    print("\n" + "="*40)
    print("📊 性能测试分析报告")
    print("="*40)
    print(f"总耗时 (真实挂钟时间): {end_total - start_total:.2f} 秒")
    print("-" * 40)
    
    print(f"【注册阶段 (Argon2 哈希生成 + DB 写入)】")
    print(f"✅ 成功: {len(register_times)} | ❌ 失败: {failed_regs}")
    if register_times:
        print(f"   ⏱️ 平均耗时: {statistics.mean(register_times)*1000:.1f} ms / 请求")
        print(f"   📈 最大耗时: {max(register_times)*1000:.1f} ms")
        print(f"   📉 最小耗时: {min(register_times)*1000:.1f} ms")
        
    print("-" * 40)
    print(f"【登录阶段 (Argon2 校验 + DB 写入 Token 与 Device)】")
    print(f"✅ 成功: {len(login_times)} | ❌ 失败: {failed_logins}")
    if login_times:
        print(f"   ⏱️ 平均耗时: {statistics.mean(login_times)*1000:.1f} ms / 请求")
        print(f"   📈 最大耗时: {max(login_times)*1000:.1f} ms")
        print(f"   📉 最小耗时: {min(login_times)*1000:.1f} ms")
    print("="*40)
    
    print("\n💡 架构洞察:")
    print("1. Argon2 密码哈希是 CPU 密集型操作，你可能会发现平均耗时在 200ms 以上，这是正常且安全的。")
    print("2. 如果发现有大量状态码 500（database is locked），说明并发写入冲突，需要确认 WAL 模式是否已正确生效。")

if __name__ == "__main__":
    test_perf()