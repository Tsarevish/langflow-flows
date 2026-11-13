name: Ошибка · дубль идентификатора
description: узел объявлен дважды

nodes:
  Vhod: ChatInput
  Otvet: ChatOutput
  Vhod: ChatInput

edges:
  Vhod.message -> Otvet.input_value
