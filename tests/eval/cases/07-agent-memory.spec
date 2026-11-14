name: E07 агент с историей
description: Память диалога через n_messages агента

nodes:
  Vhod: ChatInput
  P: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  G: Agent
  Otvet: ChatOutput

edges:
  Vhod.message -> G.input_value
  P.prompt -> G.system_prompt
  Model.model_output -> G.model
  G.response -> Otvet.input_value

config:
  P.template: |
    Ты — ассистент. Помнишь предыдущие сообщения в рамках сессии.
  Model.openai_api_base: __MODEL_BASE__
  Model.model_name: __MODEL_NAME__
  G.n_messages: 50
  G.max_iterations: 10
