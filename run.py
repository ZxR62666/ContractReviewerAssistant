# 文件名: run.py
from app import create_app

app = create_app()
    
if __name__ == '__main__':
    # 从 config.py 加载配置，但 run 方法的参数会覆盖它
    app.run(host='0.0.0.0', port=6045, debug=True)