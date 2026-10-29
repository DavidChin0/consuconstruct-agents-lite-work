name: git-hygiene-remote
description: "Use when working in consuconstruct-agents-lite repo branches. Keep main untouched; always branch+PR."
---

# Higiene de git en este repo

- Nunca commitear ni pushear directo a `main`.
- Antes de empezar una tarea nueva: `git checkout main && git pull && git checkout -b <owner>/<id>-<slug>`.
- `git status` limpio antes de cualquier commit — revisar que no se arrastren
  archivos de otra tarea.
- Nunca `git add -A` ciego: revisar `git status --short` primero y confirmar
  que cada archivo listado pertenece a esta tarea.
- Un PR por tarea. El título del PR cita el `#id` de la tarea del correo
  original, para que David y reviewer puedan rastrear el hilo.
