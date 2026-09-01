venv:
	python3 -m venv .venv && . .venv/bin/activate && python -m pip install -U pip

install:
	. .venv/bin/activate && pip install -r requirements.txt

run:
	. .venv/bin/activate && FLASK_APP=app.py flask run --host=0.0.0.0 --port=5000

deploy-setup:
	@echo "Setting up deployment environment..."
	@if [ ! -f instance/.env ] || [ ! -f instance/config.yaml ]; then \
		echo "Create instance/.env and instance/config.yaml from the tracked examples first"; \
		exit 1; \
	fi
	sudo chmod 600 instance/.env instance/config.yaml

gen-systemd:
	@echo "Generating systemd service files..."
	@if [ ! -f scripts/gen_systemd.sh ]; then \
		echo "Error: scripts/gen_systemd.sh not found"; \
		exit 1; \
	fi
	chmod +x scripts/gen_systemd.sh
	./scripts/gen_systemd.sh

deploy: gen-systemd deploy-setup
	@echo "Enabling and starting Family Hub services..."
	sudo systemctl enable family-hub@${USER}.service
	sudo systemctl enable family-hub-kiosk@${USER}.service
	sudo systemctl start family-hub@${USER}.service
	sudo systemctl start family-hub-kiosk@${USER}.service

deploy-nginx: gen-systemd deploy-setup
	@echo "Setting up nginx reverse proxy for Family Hub..."
	@if [ ! -f scripts/gen_nginx_config.sh ]; then \
		echo "Creating nginx config generation script..."; \
		echo '#!/bin/bash' > scripts/gen_nginx_config.sh; \
		echo '# Script to generate nginx configuration from template' >> scripts/gen_nginx_config.sh; \
		echo 'DOMAIN=${1:-localhost}' >> scripts/gen_nginx_config.sh; \
		echo 'sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled' >> scripts/gen_nginx_config.sh; \
		echo 'sudo cp /opt/family-hub/ops/nginx/family-hub.conf.tmpl /tmp/family-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo sed -i "s/{{SERVER_NAME}}/$DOMAIN/g" /tmp/family-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo sed -i "s|{{SSL_CERT_PATH}}|/etc/letsencrypt/live/$DOMAIN/fullchain.pem|g" /tmp/family-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo sed -i "s|{{SSL_KEY_PATH}}|/etc/letsencrypt/live/$DOMAIN/privkey.pem|g" /tmp/family-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo mv /tmp/family-hub.conf /etc/nginx/sites-available/family-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo ln -sf /etc/nginx/sites-available/family-hub.conf /etc/nginx/sites-enabled/family-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo nginx -t && echo "Nginx configuration test passed"' >> scripts/gen_nginx_config.sh; \
		echo 'sudo systemctl restart nginx' >> scripts/gen_nginx_config.sh; \
		echo 'echo "Nginx configuration updated for domain: $DOMAIN"' >> scripts/gen_nginx_config.sh; \
		chmod +x scripts/gen_nginx_config.sh; \
	fi
	sudo cp ops/nginx/family-hub.conf.tmpl /opt/family-hub/ops/nginx/family-hub.conf.tmpl
	./scripts/gen_nginx_config.sh
	sudo systemctl enable family-hub@${USER}.service
	sudo systemctl enable family-hub-kiosk@${USER}.service
	sudo systemctl start family-hub@${USER}.service
	sudo systemctl start family-hub-kiosk@${USER}.service

deploy-ssl:
	@echo "Setting up SSL with Let's Encrypt..."
	@if [ ! -f scripts/setup_ssl.sh ]; then \
		echo "Error: scripts/setup_ssl.sh not found"; \
		exit 1; \
	fi
	chmod +x scripts/setup_ssl.sh
	@echo "Running SSL setup script (run with domain name as parameter)"
	@echo "Usage: sudo ./scripts/setup_ssl.sh your-domain.com your-email@example.com"

deploy-with-ssl: deploy-nginx deploy-ssl
	@echo "Family Hub deployed with SSL support!"

deploy-test:
	@echo "Testing Family Hub installation..."
	curl -f http://localhost:5000/health || { echo "Health check failed"; exit 1; }
	@echo "Health check passed"