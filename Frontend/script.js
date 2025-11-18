// ==== Smooth scroll to agents section ====
document.getElementById('exploreBtn').addEventListener('click', () => {
  document.querySelector('#agents').scrollIntoView({ behavior: 'smooth' });
});


// ==== Open specific agent page in new tab ====
// document.querySelectorAll('.agent-card').forEach(card => {
//   card.addEventListener('click', () => {
//     const title = card.querySelector('h3').innerText;

//     // Open different pages depending on the clicked card
//     if (title.includes('Customer Support')) {
//       window.open('customer-support-agent.html', '_blank');
//     } else if (title.includes('Production')) {
//       window.open('production-agent.html', '_blank');
//     } else if (title.includes('Marketing')) {
//       window.open('marketing-agent.html', '_blank');
//     }
//   });
// });


/* ==== Open specific agent page in new tab ==== */
document.querySelectorAll('.agent-card').forEach(card => {
  card.addEventListener('click', () => {
    const page = card.dataset.page;          // e.g. customer_support_agent.html
    if (page) window.open(page, '_blank');
  });
});

/* ==== Group tab switching ==== */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    // toggle active class
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // show/hide groups
    const target = btn.dataset.group;
    document.querySelectorAll('.agent-group').forEach(g => {
      g.style.display = (g.dataset.group === target) ? 'grid' : 'none';
    });
  });
});



// ==== Fade-in animation on scroll ====
const revealElements = document.querySelectorAll('section');
window.addEventListener('scroll', () => {
  revealElements.forEach(sec => {
    const rect = sec.getBoundingClientRect();
    if (rect.top < window.innerHeight - 100) {
      sec.classList.add('visible');
    }
  });
});


// ==== Animate agent cards on scroll ====
const agentCards = document.querySelectorAll('.agent-card');
window.addEventListener('scroll', () => {
  agentCards.forEach(card => {
    const rect = card.getBoundingClientRect();
    if (rect.top < window.innerHeight - 100) {
      card.classList.add('visible');
    }
  });
});
