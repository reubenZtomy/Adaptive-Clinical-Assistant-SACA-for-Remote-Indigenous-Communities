export function Button({ className = "", children, ...props }) {
  return (
    <button
      {...props}
      className={className}
      style={{
        padding: "12px 20px",
        borderRadius: 999,
        background: "#174EB2",
        color: "#fff",
        border: "none",
        fontWeight: 700,
        cursor: "pointer",
        boxShadow: "0 10px 20px rgba(23,78,178,.25)",
        transition: "transform .15s ease, box-shadow .15s ease",
        ...(props.disabled ? { opacity: .6, cursor: "not-allowed" } : {})
      }}
      onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.03)")}
      onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1.0)")}
    >
      {children}
    </button>
  );
}