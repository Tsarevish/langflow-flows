name: E06 агент и инструмент
description: Калькулятор подключён агенту как инструмент

nodes:
  Vhod: ChatInput
  P: Prompt Template
  Model: ext:openai:OpenAIModelComponent@official
  Calc: CalculatorComponent
  G: Agent
  Otvet: ChatOutput

edges:
  Vhod.message -> G.input_value
  P.prompt -> G.system_prompt
  Model.model_output -> G.model
  Calc.component_as_tool -> G.tools
  G.response -> Otvet.input_value

config:
  P.template: |
    Ты — ассистент с калькулятором. Для любых вычислений вызывай инструмент,
    не считай в уме. В ответе — только число.
  Model.openai_api_base: https://ai.api.cloud.yandex.net/v1
  Model.model_name: gpt://b1gtacbqthmqh9b7rt0f/deepseek-v4.1-flash/latest
  Model.temperature: 0.1
