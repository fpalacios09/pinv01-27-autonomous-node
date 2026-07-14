# Política de seguridad

No reportar credenciales reales en issues públicos. Revocar inmediatamente cualquier secreto publicado.

```bash
git grep -nEi 'password|passwd|secret|token|api[_-]?key|rtsp://[^ ]+@'
```

La validación CID asegura integridad del contenido, pero no autentica por sí sola el origen del comando. Para despliegues críticos, añadir firmas de manifiestos y autorización del canal inbound.
