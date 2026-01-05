docker volume inspect <Volume>


docker stop <Volume>
docker run --rm -v <目標Volume>:/data busybox sh -c "rm -rf /data/*"
# 假設您的 Volume 名稱是 docker_meilisearch_data
docker run --rm -v meilisearch_meilisearch_data:/source -v "$(pwd)":/backup busybox tar cvzf /backup/meili_backup.tar.gz -C /source .
