name: E05 агент и база
description: Агент формирует SQL, база отвечает таблицей

nodes:
  Vhod: ChatInput
  P: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  G: Agent
  DB: SQLComponent
  Otvet: ChatOutput

edges:
  Vhod.message -> G.input_value
  P.prompt -> G.system_prompt
  Model.model_output -> G.model
  G.response -> DB.query
  DB.run_sql_query -> Otvet.input_value

config:
  P.template: |
    Ты — помощник по данным. Пользователь задаёт вопрос.
    Верни ТОЛЬКО SQL-запрос для PostgreSQL: без пояснений, без markdown-блоков,
    без точки с запятой в конце.
    Если вопрос не про данные — верни SELECT 'не могу помочь' AS message.
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
  Model.temperature: 0.1
  Model.max_tokens: 400
