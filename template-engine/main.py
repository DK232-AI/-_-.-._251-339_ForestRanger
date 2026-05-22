from engine import ModifiedTemplate

if __name__ == "__main__":
    # 1. Задаем динамические данные (контекст)
    test_context = {
        "user_input": "<script>alert('dangerous xss')</script>", # Опасный скрипт
        "items": ["Молоко", "Хлеб", "Сыр"],
        "is_authorized": True
    }

    # 2. Создаем HTML шаблон
    html_layout = """
    <div>
        <h3>Профиль пользователя</h3>
        <p>Безопасный вывод имени (защита от XSS): {{ user_input }}</p>
        <p>Вывод имени с фильтром REVERSE: {{ user_input | reverse }}</p>
        <p>Вывод неэкранированного HTML (через safe): {{ user_input | safe }}</p>

        {% if is_authorized %}
            <h4>Ваш список покупок:</h4>
            <ul>
                {% for item in items %}
                    <li>{{ item | upper }}</li>
                {% endfor %}
            </ul>
        {% endif %}
    </div>
    """

    print("=== ШАГ 1: Инициализация шаблонизатора ===")
    template = ModifiedTemplate(html_layout)
    
    print("\n=== ШАГ 2: Сгенерированный «на лету» код на Python: ===")
    print(template.code_builder)
    
    print("\n=== ШАГ 3: Результат рендеринга (Итоговый HTML): ===")
    output_html = template.render(test_context)
    print(output_html)