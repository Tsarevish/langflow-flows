name: E09 ветвление по ответу
description: Роутер делит ответ модели на две ветки

nodes:
  Vhod: ChatInput
  P: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  R: ConditionalRouter
  Da: ChatOutput
  Net: ChatOutput

edges:
  Vhod.message -> P.question
  P.prompt -> Model.input_value
  Model.text_output -> R.input_text
  R.true_result -> Da.input_value
  R.false_result -> Net.input_value

config:
  P.template: |
    Ответь одним словом: «да» или «нет». Вопрос: {question}
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
  Model.temperature: 0
  R.match_text: да
  R.operator: contains
  R.case_sensitive: false
