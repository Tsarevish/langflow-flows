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
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
