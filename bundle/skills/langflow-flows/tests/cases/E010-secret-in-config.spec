name: Ошибка · секрет в config
description: ключ задан строкой, привязка к переменной сломается

nodes:
  Vhod: ChatInput
  Model: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> Model.input_value
  Model.text_output -> Otvet.input_value

config:
  Model.api_key: OPENAI_API_KEY
  Model.openai_api_base: https://example.invalid/v1
  Model.model_name: gpt://demo/model
