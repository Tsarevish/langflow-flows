name: E11 после правки
description: Добавлен ChatOutput в конце цепочки

nodes:
  Vhod: ChatInput
  Model: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> Model.input_value
  Model.text_output -> Otvet.input_value

config:
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
  Model.max_tokens: 200
