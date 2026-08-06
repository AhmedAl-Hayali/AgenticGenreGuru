# API errors
Deezer API returns some error codes if your request failed. Here is the list of all codes and their description you can encounter.

| Constant                       | Type                                        | Code |
|--------------------------------|---------------------------------------------|------|
| QUOTA                          | Exception                                   | 4    |
| ITEMS_LIMIT_EXCEEDED           | Exception                                   | 100  |
| PERMISSION                     | OAuthException                              | 200  |
| TOKEN_INVALID                  | OAuthException                              | 300  |
| PARAMETER                      | ParameterException                          | 500  |
| PARAMETER_MISSING              | MissingParameterException                   | 501  |
| QUERY_INVALID                  | InvalidQueryException                       | 600  |
| SERVICE_BUSY                   | Exception                                   | 700  |
| DATA_NOT_FOUND                 | DataException                               | 800  |
| INDIVIDUAL_ACCOUNT_NOT_ALLOWED | IndividualAccountChangedNotAllowedException | 901  |

Sourced from [API errors](https://developers.deezer.com/api/errors).