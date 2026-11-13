name: Ошибка · ромб без опоры
description: агент без модели и без выхода

nodes:
  Vhod: ChatInput
  G: Agent
  P: Prompt Template

edges:
  Vhod.message -> G.input_value
  P.prompt -> G.system_prompt

config:
  P.template: |
    Ты — ассистент.
