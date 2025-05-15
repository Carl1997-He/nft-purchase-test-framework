import subprocess
import time
import csv
from web3 import Web3
from eth_account import Account

# 初始化 Web3
w3 = Web3(Web3.HTTPProvider("https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID"))

# 启动 JMeter 测试（模拟300用户购买请求）
print("✅ 启动 JMeter 测试...")
start = time.time()
subprocess.run([
    "jmeter", "-n", "-t", "jmeter/nft_purchase.jmx", "-l", "data/result.jtl"
])
print("✅ JMeter 执行完成")

# 读取 tx_request.csv 并处理链上交易
print("✅ 开始链上签名 + 广播 + 回执分析")

results = []
with open("data/tx_request.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            t1 = float(row["timestamp"])  # JMeter写入时间
            t2 = time.time()              # Python接收到请求时间

            private_key = row["private_key"]
            contract_address = row["contract_address"]
            data = row["encoded_data"]
            account = Account.from_key(private_key)
            nonce = w3.eth.get_transaction_count(account.address)

            txn = {
                "to": contract_address,
                "value": 0,
                "gas": 300000,
                "gasPrice": w3.to_wei("30", "gwei"),
                "nonce": nonce,
                "chainId": 11155111,
                "data": data
            }

            signed = account.sign_transaction(txn)
            t3 = time.time()  # 签名完成时间

            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            t4 = time.time()  # 广播完成时间

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            t5 = time.time()  # 链上确认完成时间

            results.append({
                "user_id": row["user_id"],
                "nft_id": row["nft_id"],
                "tx_hash": tx_hash.hex(),
                "status": receipt.status,
                "t1_jmeter": t1,
                "t2_python_received": t2,
                "t3_signed": t3,
                "t4_sent": t4,
                "t5_confirmed": t5,
                "total_delay": round(t5 - t1, 3)
            })

            print(f"✅ [{row['user_id']}] OK | tx: {tx_hash.hex()} | delay: {round(t5 - t1, 2)}s")
        except Exception as e:
            print(f"❌ [{row['user_id']}] FAILED: {str(e)}")

# 写入分析结果 CSV
with open("data/tx_analysis.csv", "w", newline="") as f:
    fieldnames = ["user_id", "nft_id", "tx_hash", "status",
                  "t1_jmeter", "t2_python_received", "t3_signed",
                  "t4_sent", "t5_confirmed", "total_delay"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print("✅ 所有交易处理完成，结果已写入 data/tx_analysis.csv")
