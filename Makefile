lint:
	terraform fmt infra \
	&& ruff --fix . \
	&& black . \
	&& mypy .

clean:
	rm infra/terraform.tfstate.backup*

build:
	docker build -t rostmoguchiy/tts-server:latest --platform linux/amd64 -f tts-server.Dockerfile . \
	&& docker build -t rostmoguchiy/notifications-server:latest --platform linux/amd64 -f notifications-server.Dockerfile .

push:
	docker push rostmoguchiy/tts-server \
	&& docker push rostmoguchiy/notifications-server
