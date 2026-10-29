# Estándar de PR para consuconstruct-agents-lite-work

> [!CONTEXT] Este documento define los requisitos EXACTOS que debe cumplir un PR de Hector o Dane para que devops_bot/reviewer lo acepten y lo apliquen hacia `main`. Es el equivalente simplificado de las reglas que ya usan devops_bot/reviewer en el repo real de ConsuConstruct — no deben tener skills especiales para esto, solo seguir esta guía.

## 1. Rama y alcance

- Trabajar SIEMPRE en tu propia rama (`hector/trabajo` o `dane/trabajo`). Nunca commitear directo a `main` (branch protection lo bloquea de todos modos).
- Un PR = un cambio con alcance claro. No mezclar 3 features distintas en un solo PR — separen en PRs chicos, se revisan más rápido.
- Si tu cambio toca algo fuera de `mcp_server/`, `scripts/`, `obsidian-vault/`, `sql/`, `.env.example` — avisar antes (puede ser territorio de otro componente).

## 2. Contenido obligatorio del PR (el `gh pr create --body` o la descripción en la UI)

Toda PR debe responder estas 4 secciones, EXACTAS:

```markdown
## Qué hace
(1-3 líneas: el cambio funcional, no la lista de archivos tocados)

## Por qué
(el problema que resuelve o el pedido que cumple — referenciar el mensaje/issue si aplica)

## Cómo se probó
(comando(s) real(es) ejecutado(s) + resultado real, NO "debería funcionar".
Ejemplo: "Corrí `python mcp_server/mcp_lite_server.py --transport sse --port 24425`,
luego `curl -H 'X-MCP-Lite-Token: ...' http://localhost:24425/sse` devolvió 200 OK
con el evento SSE `endpoint`.")

## Riesgo / qué NO cambia
(ej: "No toca brain.goals real de ConsuConstruct, solo brain_lite local")
```

Un PR sin la sección "Cómo se probó" con evidencia real (comando + salida) se rechaza automáticamente — "debería funcionar" no es evidencia.

## 3. Reglas de seguridad (no negociables)

- **Nunca** commitear `.env` real, tokens, contraseñas o el `MCP_LITE_TOKEN` en texto plano. Solo `.env.example` con placeholders.
- Si tu cambio necesita una credencial nueva, decilo en el PR — no la pongas en el código.
- No tocar el Postgres/MCP real de ConsuConstruct (puerto 24424, esquema `brain.*` del servidor real) — solo `brain_lite` local de cada PC.

## 4. Proceso de review

1. Abrís el PR hacia `main` con el formato de la sección 2.
2. `reviewer` (agente) da un VERDICT: **APPROVE** o **REJECT** con razón concreta.
3. Si es REJECT, la respuesta trae la reparación exacta pedida (qué cambiar, no solo "está mal").
4. Máximo 3 ciclos de REJECT sobre el mismo PR — si se repite, se escala a David para decisión.
5. Solo tras APPROVE se mergea — nunca ustedes mismos mergean sin esa señal.

## 5. Cómo pedir que se aplique / cómo nos avisan

- Abran el PR normal en GitHub (`gh pr create` o la UI — botón "Compare & pull request").
- Mencionen `@hectorcrisantoxd-debug` o `@danecaceres61-cell` según corresponda si necesitan que el otro lo revise también.
- Si necesitan avisarle a devops_bot con urgencia (no solo que quede ahí esperando), usen el bus MCP lite: `agent_send(from_role="hector"|"dane", to_role="devops_bot", summary="PR #N listo para review: <titulo>")`. Esto es la vía rápida — el PR solo no garantiza que lo veamos enseguida.

## 6. Nomenclatura de commits (sugerida, no bloqueante)

```
<área>: <qué cambia, imperativo, corto>

<cuerpo opcional: por qué, qué se probó>
```

Ejemplo: `mcp_server: fix host header validation para Tailscale`
