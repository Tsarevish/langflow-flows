name: E08 два шага промпта
description: Ответ модели уходит во второй промпт и во вторую модель

nodes:
  Vhod: ChatInput
  P1: Prompt Template
  M1: ext:openai:OpenAIModelComponent@official
  P2: Prompt Template
  M2: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> P1.question
  P1.prompt -> M1.input_value
  M1.text_output -> P2.otvet
  P2.prompt -> M2.input_value
  M2.text_output -> Otvet.input_value

config:
  P1.template: |
    Ответь на вопрос одним словом: {question}
  P2.template: |
    Переведи на английский, только перевод: {otvet}
  M1.openai_api_base: __MODEL_BASE__
  M1.model_name: __MODEL_NAME__
  M1.temperature: 0.1
  M1.max_tokens: 50
  M2.openai_api_base: __MODEL_BASE__
  M2.model_name: __MODEL_NAME__
  M2.temperature: 0.1
  M2.max_tokens: 50
