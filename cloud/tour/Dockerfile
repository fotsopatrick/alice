FROM odoo:18

# Compat : requests est requis par les agents Chloé/Braignak.
USER root
RUN pip3 install --no-cache-dir --break-system-packages requests \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=odoo:odoo custom-addons /mnt/extra-addons
COPY --chown=odoo:odoo odoo.conf /etc/odoo/odoo.conf
COPY --chown=odoo:odoo entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER odoo
EXPOSE 8069
ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]