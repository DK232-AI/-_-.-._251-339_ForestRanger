import re
import html

# Реестр доступных фильтров
FILTERS = {
    "upper": lambda x: str(x).upper(),
    "lower": lambda x: str(x).lower(),
    "reverse": lambda x: str(x)[::-1],
    "safe": lambda x: x  # Фильтр, отменяющий автоматическое экранирование HTML
}

class CodeBuilder:
    """Управляет динамической генерацией Python-кода с соблюдением отступов."""
    def __init__(self):
        self.code = []          # Список строк генерируемого кода
        self.indent_level = 0   # Текущий уровень вложенности

    def add_line(self, line):
        """Добавляет строку кода с учетом текущего уровня отступа."""
        self.code.append("    " * self.indent_level + line)

    def indent(self):
        """Увеличивает отступ (вход в блок if, for, def)."""
        self.indent_level += 1

    def dedent(self):
        """Уменьшает отступ (выход из блока)."""
        self.indent_level -= 1

    def get_globals(self):
        """Компилирует накопленный код и возвращает глобальное пространство имен с зависимостями."""
        code_string = str(self)
        
        # Передаем импортированный html и словарь FILTERS внутрь контекста exec()
        global_vars = {
            "html": html,
            "FILTERS": FILTERS
        }
        
        exec(code_string, global_vars)
        return global_vars

    def __str__(self):
        return "\n".join(self.code)


class Template:
    """Базовый компилирующий шаблонизатор."""
    def __init__(self, template_text):
        self.raw_text = template_text
        self.code_builder = CodeBuilder()
        self.render_func = None
        self.compile()

    def compile(self):
        # Разбиваем текст по тегам {{ ... }} и {% ... %}
        tokens = re.split(r"(\{\{.*?\}\}|\{\%.*?\%\})", self.raw_text, flags=re.DOTALL)
        
        # Сигнатура генерируемой функции
        self.code_builder.add_line("def render_function(context):")
        self.code_builder.indent()
        self.code_builder.add_line("result = []")
        
        # Переносим переменные из словаря context в локальную область видимости Python
        self.code_builder.add_line("for key, val in context.items():")
        self.code_builder.indent()
        self.code_builder.add_line("globals()[key] = val")
        self.code_builder.dedent()
        
        # Трансляция токенов
        self._parse_tokens(tokens)
        
        self.code_builder.add_line("return ''.join(result)")
        self.code_builder.dedent()
        
        # Компилируем собранный текст в исполняемый объект функции
        compiled_globals = self.code_builder.get_globals()
        self.render_func = compiled_globals["render_function"]

    def _parse_tokens(self, tokens):
        for token in tokens:
            if not token:
                continue
            
            # Если это вывод переменной: {{ user.name }}
            if token.startswith("{{"):
                var_name = token[2:-2].strip()
                self.code_builder.add_line(f"result.append(str({var_name}))")
                
            # Если это блок логики: {% if ... %} или {% for ... %}
            elif token.startswith("{%"):
                words = token[2:-2].strip().split()
                instruction = words[0]
                
                if instruction == "for":
                    loop_expr = " ".join(words[1:])
                    self.code_builder.add_line(f"for {loop_expr}:")
                    self.code_builder.indent()
                elif instruction == "if":
                    cond_expr = " ".join(words[1:])
                    self.code_builder.add_line(f"if {cond_expr}:")
                    self.code_builder.indent()
                elif instruction in ("endfor", "endif"):
                    self.code_builder.dedent()
                    
            # Если это обычный статический текст
            else:
                safe_text = repr(token)
                self.code_builder.add_line(f"result.append({safe_text})")

    def render(self, context):
        """Вызывает скомпилированную функцию с переданными данными."""
        return self.render_func(context)


class ModifiedTemplate(Template):
    """Модифицированный шаблонизатор с авто-экранированием HTML (XSS защита) и фильтрами."""
    def _parse_tokens(self, tokens):
        for token in tokens:
            if not token:
                continue
            
            # Обработка переменных с поддержкой фильтров и XSS-защиты
            if token.startswith("{{"):
                expression = token[2:-2].strip()
                
                if "|" in expression:
                    parts = expression.split("|")
                    var_name = parts[0].strip()
                    filters_list = [p.strip() for p in parts[1:]]
                    
                    # Генерируем цепочку вызовов фильтров
                    expr_str = var_name
                    is_safe = False
                    for f in filters_list:
                        if f == "safe":
                            is_safe = True
                            continue
                        if f in FILTERS:
                            expr_str = f"FILTERS['{f}']({expr_str})"
                    
                    # Если фильтр "safe" не применен, экранируем HTML по умолчанию
                    if not is_safe:
                        self.code_builder.add_line(f"result.append(html.escape(str({expr_str})))")
                    else:
                        self.code_builder.add_line(f"result.append(str({expr_str}))")
                else:
                    # Экранирование переменной по умолчанию
                    self.code_builder.add_line(f"result.append(html.escape(str({expression})))")
            
            # Логические блоки
            elif token.startswith("{%"):
                words = token[2:-2].strip().split()
                instruction = words[0]
                if instruction == "for":
                    self.code_builder.add_line(f"for {' '.join(words[1:])}:")
                    self.code_builder.indent()
                elif instruction == "if":
                    self.code_builder.add_line(f"if {' '.join(words[1:])}:")
                    self.code_builder.indent()
                elif instruction in ("endfor", "endif"):
                    self.code_builder.dedent()
            
            # Статический текст
            else:
                safe_text = repr(token)
                self.code_builder.add_line(f"result.append({safe_text})")