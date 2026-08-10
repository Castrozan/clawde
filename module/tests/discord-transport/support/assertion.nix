{
  lib,
}:
let
  stringify =
    value:
    if value == null then
      "null"
    else if builtins.isBool value then
      (if value then "true" else "false")
    else
      toString value;

  assertion = name: expected: actual: {
    inherit name expected actual;
  };

  assertContains =
    name: expectedFragment: actual:
    assertion name "contains ${expectedFragment}" (
      if builtins.isString actual && builtins.match ".*${expectedFragment}.*" actual != null then
        "contains ${expectedFragment}"
      else
        actual
    );

  assertLacks =
    name: forbiddenFragment: actual:
    assertion name "lacks ${forbiddenFragment}" (
      if builtins.isString actual && builtins.match ".*${forbiddenFragment}.*" actual == null then
        "lacks ${forbiddenFragment}"
      else
        actual
    );

  failedAssertionMessagesFor =
    evaluated:
    map (assertionEntry: assertionEntry.message) (
      lib.filter (assertionEntry: !assertionEntry.assertion) evaluated.config.assertions
    );
in
{
  inherit
    stringify
    assertion
    assertContains
    assertLacks
    failedAssertionMessagesFor
    ;
}
