name: E03 промпт-чейн
description: Правило в отдельном узле, переменная из чата

nodes:
  Vhod: ChatInput
  P: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> P.question
  P.prompt -> Model.input_value
  Model.text_output -> Otvet.input_value

config:
  P.template: |
    Ответь одним предложением, без вступлений: {question}
  Model.openai_api_base: __MODEL_BASE__
  Model.model_name: __MODEL_NAME__
  Model.temperature: 0.1
