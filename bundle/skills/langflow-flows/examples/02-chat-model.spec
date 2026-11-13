name: 02 Чат с моделью
description: Один вызов модели, ответ в чат

nodes:
  Vhod: ChatInput
  Model: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> Model.input_value
  Model.text_output -> Otvet.input_value

config:
  Model.openai_api_base: <адрес модели из профиля стенда>
  Model.model_name: <имя модели из профиля стенда>
  Model.temperature: 0.2
  Model.max_tokens: 600
