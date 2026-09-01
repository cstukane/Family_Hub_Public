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
	@echo "Enabling and starting Kitchen Hub services..."
	sudo systemctl enable kitchen-hub@${USER}.service
	sudo systemctl enable kitchen-hub-kiosk@${USER}.service
	sudo systemctl start kitchen-hub@${USER}.service
	sudo systemctl start kitchen-hub-kiosk@${USER}.service

deploy-nginx: gen-systemd deploy-setup
	@echo "Setting up nginx reverse proxy for Kitchen Hub..."
	@if [ ! -f scripts/gen_nginx_config.sh ]; then \
		echo "Creating nginx config generation script..."; \
		echo '#!/bin/bash' > scripts/gen_nginx_config.sh; \
		echo '# Script to generate nginx configuration from template' >> scripts/gen_nginx_config.sh; \
		echo 'DOMAIN=${1:-localhost}' >> scripts/gen_nginx_config.sh; \
		echo 'sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled' >> scripts/gen_nginx_config.sh; \
		echo 'sudo cp /opt/kitchen-hub/ops/nginx/kitchen-hub.conf.tmpl /tmp/kitchen-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo sed -i "s/{{SERVER_NAME}}/$DOMAIN/g" /tmp/kitchen-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo sed -i "s|{{SSL_CERT_PATH}}|/etc/letsencrypt/live/$DOMAIN/fullchain.pem|g" /tmp/kitchen-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo sed -i "s|{{SSL_KEY_PATH}}|/etc/letsencrypt/live/$DOMAIN/privkey.pem|g" /tmp/kitchen-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo mv /tmp/kitchen-hub.conf /etc/nginx/sites-available/kitchen-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo ln -sf /etc/nginx/sites-available/kitchen-hub.conf /etc/nginx/sites-enabled/kitchen-hub.conf' >> scripts/gen_nginx_config.sh; \
		echo 'sudo nginx -t && echo "Nginx configuration test passed"' >> scripts/gen_nginx_config.sh; \
		echo 'sudo systemctl restart nginx' >> scripts/gen_nginx_config.sh; \
		echo 'echo "Nginx configuration updated for domain: $DOMAIN"' >> scripts/gen_nginx_config.sh; \
		chmod +x scripts/gen_nginx_config.sh; \
	fi
	sudo cp ops/nginx/kitchen-hub.conf.tmpl /opt/kitchen-hub/ops/nginx/kitchen-hub.conf.tmpl
	./scripts/gen_nginx_config.sh
	sudo systemctl enable kitchen-hub@${USER}.service
	sudo systemctl enable kitchen-hub-kiosk@${USER}.service
	sudo systemctl start kitchen-hub@${USER}.service
	sudo systemctl start kitchen-hub-kiosk@${USER}.service

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
	@echo "Kitchen Hub deployed with SSL support!"

deploy-test:
	@echo "Testing Kitchen Hub installation..."
	curl -f http://localhost:5000/health || { echo "Health check failed"; exit 1; }
	@echo "Health check passed"