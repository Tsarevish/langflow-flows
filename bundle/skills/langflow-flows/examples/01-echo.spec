name: 01 Эхо
description: Минимум для проверки связки с инстансом

nodes:
  Vhod: ChatInput
  Otvet: ChatOutput

edges:
  Vhod.message -> Otvet.input_value
