from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """덧셈 : 두 수를 더합니다. a + b"""
    print(f"덧셈 : {a} + {b}")
    return a + b

@tool
def subtract(a: int, b: int) -> int:
    """뺄셈 : 두 수를 뺍니다. a - b"""
    print(f"뺄셈 : {a} - {b}")
    return a - b

@tool
def multiply(a: int, b: int) -> int:
    """곱셈 : 두 수를 곱합니다. a * b"""
    print(f"곱셈 : {a} * {b}")
    return a * b

@tool
def divide(a: int, b: int) -> int:
    """나눗셈 : 두 수를 나눕니다. a / b"""
    print(f"나눗셈 : {a} / {b}")
    return a / b

@tool
def square(a: int) -> int:
    """제곱(square) : 수의 제곱을 계산합니다. a ^ 2"""
    print(f"제곱 : {a} ^ 2")
    return a ** 2

@tool
def square_root(a: int) -> int:
    """제곱근(square_root) : 수의 제곱근을 계산합니다. sqrt(a)"""
    print(f"제곱근 : sqrt({a})")
    return a ** 0.5

