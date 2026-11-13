name: Ошибка · связь в пустоту
description: ребро ссылается на узел, которого нет

nodes:
  Vhod: ChatInput
  Otvet: ChatOutput

edges:
  Vhod.message -> Otvet.input_value
  Ghost.message -> Otvet.input_value
