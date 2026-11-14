name: E02 чат с моделью
description: Один вызов модели

nodes:
  Vhod: ChatInput
  Model: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> Model.input_value
  Model.text_output -> Otvet.input_value

config:
  Model.openai_api_base: __MODEL_BASE__
  Model.model_name: __MODEL_NAME__
  Model.temperature: 0.1
  Model.max_tokens: 300
