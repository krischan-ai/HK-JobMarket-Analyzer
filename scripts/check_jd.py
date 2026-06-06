"""检查当前已爬取岗位的 JD 完整性"""
import json

with open("data/raw/jobsdb_raw.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"总岗位数: {len(data)}")
print()

# JD 长度统计
lens = [len(j.get("jd_raw", "")) for j in data]
avg = sum(lens) // len(lens) if lens else 0
print(f"平均 JD 长度: {avg} 字")
print(f"最短 JD: {min(lens)} 字")
print(f"最长 JD: {max(lens)} 字")
print(f"JD > 300字: {sum(1 for l in lens if l > 300)}/{len(data)}")
print(f"JD > 1000字: {sum(1 for l in lens if l > 1000)}/{len(data)}")
print()

# 按 JD 长度分组
groups = [(0, 50), (51, 100), (101, 300), (301, 1000), (1001, 99999)]
for lo, hi in groups:
    count = sum(1 for l in lens if lo <= l <= hi)
    label = f"{lo}-{hi}" if hi < 99999 else f"{lo}+"
    print(f"  JD {label}字: {count} 条")

print()

# 显示最新几条
print("--- 最新 5 条 ---")
for j in data[-5:]:
    jd_len = len(j.get("jd_raw", ""))
    print(f"  {j['title'][:40]:40s} | JD={jd_len:5d}字 | {j['company'][:25]}")

print()

# 显示未抓取完整的
short = [j for j in data if len(j.get("jd_raw", "")) <= 300]
print(f"--- {len(short)} 条 JD <= 300字（需要补充）---")
for j in short[:5]:
    print(f"  {j['title'][:45]:45s} | JD={len(j.get('jd_raw','')):4d}字 | url={j.get('url','')[:60]}")
