name: E10 после правки
description: Добавлен промпт с переменной и снижена температура

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
    Отвечай строго одним словом, без пояснений: {question}
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
  Model.temperature: 0
