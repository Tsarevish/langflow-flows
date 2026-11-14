name: E12 составной
description: Агент с инструментом и историей, ответ в чат

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
    Ты — ассистент. Всегда используй калькулятор для арифметики,
    даже если пример простой. В ответе — только число и одна строка пояснения.
  Model.openai_api_base: __MODEL_BASE__
  Model.model_name: __MODEL_NAME__
  Model.temperature: 0.1
  G.n_messages: 20
  G.max_iterations: 12
