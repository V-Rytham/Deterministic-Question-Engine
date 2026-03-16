export default function QuestionCard({ question, index }) {
  return (
    <article className="question-card">
      <h3>Question {index + 1}</h3>
      <p className="question-text">{question.question}</p>
      <ul>
        {question.options.map((option, optionIndex) => (
          <li key={`${question.question_id || index}-${optionIndex}`}>
            <label>
              <input type="radio" name={`question-${index}`} readOnly /> {option}
            </label>
          </li>
        ))}
      </ul>
    </article>
  );
}
