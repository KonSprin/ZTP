Feature: Zarzadzanie uzytkownikami
    Scenario: Utworzenie nowego uzytkownika
        Given API dziala
        When wysylam żądanie POST na "/users" z:
            | name | email        |
            | Jan  | jan@test.com |
        Then odpowiedź ma status 200
        And odpowiedź zawiera uzytkownika "Jan"
