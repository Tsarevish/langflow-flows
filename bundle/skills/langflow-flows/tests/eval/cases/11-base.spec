name: E11 база без выхода
description: Цепочка обрывается на модели

nodes:
  Vhod: ChatInput
  Model: ext:openai:OpenAIModelComponent@official

edges:
  Vhod.message -> Model.input_value

config:
  Model.openai_api_base: __MODEL_BASE__
  Model.model_name: __MODEL_NAME__
  Model.max_tokens: 200
