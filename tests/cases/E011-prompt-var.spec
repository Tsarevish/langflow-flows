name: Ошибка · порт не совпадает с переменной
description: соединено в vopros, а в шаблоне question

nodes:
  Vhod: ChatInput
  P: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  Otvet: ChatOutput

edges:
  Vhod.message -> P.vopros
  P.prompt -> Model.input_value
  Model.text_output -> Otvet.input_value

config:
  P.template: |
    Ответь на вопрос: {question}
  Model.openai_api_base: https://example.invalid/v1
  Model.model_name: gpt://demo/model
