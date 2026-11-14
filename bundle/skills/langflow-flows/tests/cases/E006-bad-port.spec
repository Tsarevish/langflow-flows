name: Ошибка · нет такого порта
description: у модели нет выхода output

nodes:
  Vhod: ChatInput
  Model: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> Model.input_value
  Model.output -> Otvet.input_value

config:
  Model.openai_api_base: https://example.invalid/v1
  Model.model_name: demo-model
