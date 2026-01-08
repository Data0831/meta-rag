docker build -t my-scheduler-app .
docker image ls
docker run -d --name scheduler-container --restart unless-stopped --init --ipc=host my-scheduler-app
docker ps
docker logs -f scheduler-container
# 匯出映像檔
docker save -o my-scheduler-app.tar my-scheduler-app

# 在目標機器上載入映像檔
docker load -i my-scheduler-app.tar
