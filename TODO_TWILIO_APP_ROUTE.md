# TODO - Criar rota Twilio no app.py

- [ ] Implementar uma rota @app.route para disparo/registro de notificação Twilio.
- [ ] A rota deve ser segura: apenas permitir POST com payload válido (ex: extintor_id, motivo).
- [ ] A rota deve chamar `enviar_notificacao_manutencao(extintor_id, motivo)`.
- [ ] Retornar JSON com status (ok / erro / Twilio não configurado).
- [ ] Validar com `python -m py_compile app.py`.
- [ ] Testar no Thunder Client: POST /twilio/notificar ou similar.

