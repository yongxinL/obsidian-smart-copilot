---
domain: testing
name: testing-standards
updated: 2025-01-01
confidence: 0.9
tags: [testing, unit, integration, coverage, mocks, typescript]
---
# Testing Standards

## Rule: Test behavior, not implementation

Tests should verify what code does, not how it does it. Test public interfaces.
Don't test private functions or internal state directly.

```typescript
// ✅ Correct: test behavior
test('login returns a JWT when credentials are valid', async () => {
  const result = await loginUser({ email: 'test@example.com', password: 'password123' });
  expect(result.token).toBeDefined();
  expect(typeof result.token).toBe('string');
});
```

```typescript
// ❌ Anti-pattern: testing implementation details
test('login calls bcrypt.compare', async () => {
  const spy = jest.spyOn(bcrypt, 'compare');
  await loginUser({ email: 'test@example.com', password: 'password123' });
  expect(spy).toHaveBeenCalled(); // brittle — breaks on refactor
});
```

---

## Rule: Use the AAA pattern (Arrange-Act-Assert)

Structure every test with three clear sections.

```typescript
// ✅ Correct: clear AAA structure
test('createUser saves to database and returns the user', async () => {
  // Arrange
  const userData = { email: 'new@example.com', name: 'Alice', password: 'secure123' };

  // Act
  const user = await createUser(userData);

  // Assert
  expect(user.id).toBeDefined();
  expect(user.email).toBe(userData.email);
  expect(user.password).toBeUndefined(); // password never returned
});
```

---

## Rule: Mock at the boundary, not deep inside

Mock external services (databases, HTTP calls, queues) at their entry point.
Don't mock internal helper functions.

```typescript
// ✅ Correct: mock the DB client
jest.mock('../lib/db', () => ({
  user: {
    create: jest.fn().mockResolvedValue({ id: '1', email: 'test@example.com' }),
    findUnique: jest.fn(),
  }
}));
```

```typescript
// ❌ Anti-pattern: mocking internal helpers
jest.mock('../lib/hashPassword'); // too deep, brittle
```

---

## Rule: Test error paths explicitly

Every function that can fail must have at least one test for the failure case.

```typescript
// ✅ Correct: test the error path
test('login throws AuthError when password is wrong', async () => {
  await expect(
    loginUser({ email: 'test@example.com', password: 'wrongpassword' })
  ).rejects.toThrow('Invalid credentials');
});
```

---

## Coverage Targets

Maintain these minimum coverage thresholds:
- Statements: 80%
- Branches: 75%
- Functions: 85%

Coverage is a floor, not a ceiling. Aim for meaningful tests, not 100% coverage.
