name: E11 база без выхода
description: Цепочка обрывается на модели

nodes:
  Vhod: ChatInput
  Model: ext:openai:OpenAIModelComponent@official

edges:
  Vhod.message -> Model.input_value

config:
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
  Model.max_tokens: 200
