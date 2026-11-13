name: E04 агент с правилами
description: Промпт в system_prompt, модель в model

nodes:
  Vhod: ChatInput
  P: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  G: Agent
  Otvet: ChatOutput

edges:
  Vhod.message -> G.input_value
  P.prompt -> G.system_prompt
  Model.model_output -> G.model
  G.response -> Otvet.input_value

config:
  P.template: |
    Ты — лаконичный ассистент. Отвечай не длиннее одного предложения.
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
  Model.temperature: 0.2
