name: E01 эхо
description: Проверка связки, без модели

nodes:
  Vhod: ChatInput
  Otvet: ChatOutput

edges:
  Vhod.message -> Otvet.input_value
