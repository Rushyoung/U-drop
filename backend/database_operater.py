import sqlite3
import sys
from core.config import settings

def main():
    # 使用统一配置文件中的数据库路径
    db_path = settings.DB_NAME
    print(f"--- U-Drop Database Operator ---")
    print(f"Connecting to: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        print("Enter SQL statements. End with ';' to execute. Type 'exit' to quit.")
        
        buffer = ""
        while True:
            prompt = "sql> " if not buffer else "  ..> "
            try:
                line = input(prompt)
            except EOFError:
                break
                
            if line.strip().lower() in ('exit', 'quit'):
                break
            
            buffer += " " + line
            
            # 只有遇到分号才执行，支持多行输入
            if buffer.strip().endswith(';'):
                sql = buffer.strip()
                buffer = ""
                
                try:
                    # 使用 executescript 支持多行脚本，或者 execute 支持单条语句
                    # 如果包含多个分号，判定为脚本
                    if sql.count(';') > 1:
                        cur.executescript(sql)
                        conn.commit()
                        print("Script executed successfully.")
                    else:
                        cur.execute(sql)
                        if sql.lstrip().upper().startswith('SELECT'):
                            rows = cur.fetchall()
                            if not rows:
                                print("Empty result.")
                            else:
                                # 简单格式化输出头
                                keys = rows[0].keys()
                                print(" | ".join(keys))
                                print("-" * (len(" | ".join(keys)) + 4))
                                for row in rows:
                                    print(" | ".join(str(row[k]) for k in keys))
                        else:
                            conn.commit()
                            print(f"OK, {cur.rowcount} row(s) affected.")
                except sqlite3.Error as e:
                    print(f"SQL Error: {e}")
                except Exception as e:
                    print(f"Error: {e}")
                    
    except Exception as e:
        print(f"Connection Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
        print("Goodbye.")

if __name__ == "__main__":
    main()
