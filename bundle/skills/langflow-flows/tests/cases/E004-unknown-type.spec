name: Ошибка · неизвестный тип
description: OpenAIModel не существует

nodes:
  Vhod: ChatInput
  Model: OpenAIModel
  Otvet: ChatOutput

edges:
  Vhod.message -> Model.input_value
  Model.text_output -> Otvet.input_value
