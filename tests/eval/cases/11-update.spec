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
  Model.openai_api_base: __MODEL_BASE__
  Model.model_name: __MODEL_NAME__
  Model.max_tokens: 200
