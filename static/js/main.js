/**
 * Variables
 */

const SESSION_TTL_MS = 30 * 60 * 1000  // 30 minutes

let chatName = ''
let chatSocket = null
let chatWindowUrl = window.location.href
let chatUuid = null
let ratingValues = {}

/**
 * Session persistence helpers
 */

function saveSession() {
    const session = {
        uuid: chatUuid,
        name: chatName,
        timestamp: Date.now()
    }
    localStorage.setItem('chatSession', JSON.stringify(session))
}

function loadSession() {
    try {
        const raw = localStorage.getItem('chatSession')
        if (!raw) return null

        const session = JSON.parse(raw)
        const elapsed = Date.now() - session.timestamp

        if (elapsed > SESSION_TTL_MS) {
            // Session expired — close the room on the server
            fetch(`/api/close_room/${session.uuid}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            localStorage.removeItem('chatSession')
            return null
        }

        return session
    } catch (e) {
        localStorage.removeItem('chatSession')
        return null
    }
}

function clearSession() {
    localStorage.removeItem('chatSession')
}

/**
 * Elements
 */

const chatElement = document.querySelector('#chat')
const chatOpenElement = document.querySelector('#chat_open')
const chatJoinElement = document.querySelector('#chat_join')
const chatIconElement = document.querySelector('#chat_icon')
const chatWelcomeElement = document.querySelector('#chat_welcome')
const chatRoomElement = document.querySelector('#chat_room')
const chatNameElement = document.querySelector('#chat_name')
const chatLogElement = document.querySelector('#chat_log')
const chatInputElement = document.querySelector('#chat_message_input')
const chatSubmitElement = document.querySelector('#chat_message_submit')
const closeBtn = document.querySelector("#closeBtn")
const fullscreenBtn = document.querySelector("#fullscreenBtn")
const chatRatingElement = document.querySelector('#chat_rating')
const ratingSubmitBtn = document.querySelector('#rating_submit')
const ratingSkipBtn = document.querySelector('#rating_skip')
const ratingCommentElement = document.querySelector('#rating_comment')
const ratingThankYouElement = document.querySelector('#rating_thank_you')
const ratingErrorElement = document.querySelector('#rating_error')

/**
 * Functions
 */

function scrollToBottom() {
    chatLogElement.scrollTop = chatLogElement.scrollHeight
}

function getCookie(name) {
    var cookieValue = null

    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';')
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim()
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
                break
            }
        }
    }
    return cookieValue
}

function sendMessage() {
    const message = chatInputElement.value.trim()

    if (!message) {
        return
    }

    chatSocket.send(JSON.stringify({
        'type': 'message',
        'message': message,
        'name': chatName,
    }))

    chatInputElement.value = ''
}

function renderMessage(data) {
    if (data.agent) {
        chatLogElement.innerHTML += `
        <div class="flex w-full mt-2 space-x-3 max-w-md">
            
            <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-300 text-center pt-2">
                ${data.initials}
            </div>       
            
            <div>
                <div class="bg-gray-300 p-3 rounded-r-lg rounded-bl-lg">
                    <p class="text-sm">${data.message}</p>
                </div>
            
                <span class="text-xs text-gray-500 leading-none">
                    ${data.created_at}
                </span>
            </div>
        </div>`

    } else {
        chatLogElement.innerHTML += `
        <div class="flex w-full mt-2 space-x-3 max-w-md ml-auto justify-end">         
            
            <div>
                <div class="bg-blue-300 p-3 rounded-l-lg rounded-br-lg">
                    <p class="text-sm">${data.message}</p>
                </div>
            
                <span class="text-xs text-gray-500 leading-none">
                    ${data.created_at}
                </span>
            </div>

            <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-300 text-center pt-2">
                ${data.initials}
            </div>
        </div>`
    }
}

function onChatMessage(data) {
    console.log('onChatMessage', data)

    if (data.type == 'chat_message') {

        let tmpInfo = document.querySelector('.tmp-info')

        if (tmpInfo) {
            tmpInfo.remove()
        }

        renderMessage(data)

    } else if (data.type == 'chat_history') {
        // Received message history on reconnect
        console.log('Received chat history:', data.messages.length, 'messages')

        // Clear the default welcome text before rendering history
        chatLogElement.innerHTML = ''

        data.messages.forEach(function(msg) {
            renderMessage(msg)
        })

    } else if (data.type == 'users_update') {
        chatLogElement.innerHTML += `<p class="mt-2 bg-gray-300 p-1 rounded-xl text-center text-gray-600">Agent has joined the chat.</p>`
    } else if (data.type == 'writing_active') {
    
        if (data.agent) {
            let tmpInfo = document.querySelector('.tmp-info')

            if (tmpInfo) {
                tmpInfo.remove()
            }

            chatLogElement.innerHTML += `
                <div class="tmp-info flex w-full mt-2 space-x-3 max-w-md">
                    
                    <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-300 text-center pt-2">
                        ${data.initials}
                    </div>       
                    
                    <div>
                        <div class="bg-gray-300 p-3 rounded-r-lg rounded-bl-lg">
                            <p class="text-sm">typing...</p>
                        </div>
                    </div>
                </div>`
        }
    } else if (data.type == 'room_closed') {
        chatLogElement.innerHTML += `<p class="mt-2 bg-gray-300 p-1 rounded-xl text-center text-gray-600">The conversation has been closed.</p>`
        showRatingForm()
    }

    scrollToBottom()

    saveSession()  // Update timestamp to keep session alive
}

function showRatingForm() {
    chatRoomElement.classList.add('hidden')
    chatRatingElement.classList.remove('hidden')
    ratingValues = {}
    initStarRatings()
}

function initStarRatings() {
    document.querySelectorAll('.star-rating').forEach(function(group) {
        const field = group.dataset.field
        const buttons = group.querySelectorAll('.star-btn')

        buttons.forEach(function(btn) {
            btn.addEventListener('click', function() {
                const value = parseInt(btn.dataset.value)
                ratingValues[field] = value

                buttons.forEach(function(b) {
                    const v = parseInt(b.dataset.value)
                    if (v <= value) {
                        b.classList.remove('text-gray-300')
                        b.classList.add('text-yellow-400')
                    } else {
                        b.classList.remove('text-yellow-400')
                        b.classList.add('text-gray-300')
                    }
                })
            })
        })
    })
}

async function submitRating() {
    if (!ratingValues.overall_rating) {
        ratingErrorElement.textContent = 'Please select an overall rating.'
        ratingErrorElement.classList.remove('hidden')
        return
    }

    ratingErrorElement.classList.add('hidden')

    const payload = {
        overall_rating: ratingValues.overall_rating,
        responsiveness: ratingValues.responsiveness || null,
        helpfulness: ratingValues.helpfulness || null,
        comment: ratingCommentElement.value.trim(),
    }

    try {
        const response = await fetch(`/api/submit_rating/${chatUuid}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify(payload),
        })

        const data = await response.json()

        if (response.ok) {
            ratingSubmitBtn.classList.add('hidden')
            ratingSkipBtn.classList.add('hidden')
            ratingThankYouElement.classList.remove('hidden')
            clearSession()

            setTimeout(function() {
                chatRatingElement.classList.add('hidden')
                chatIconElement.classList.remove('hidden')
            }, 2000)
        } else {
            ratingErrorElement.textContent = data.error || 'Something went wrong.'
            ratingErrorElement.classList.remove('hidden')
        }
    } catch (err) {
        ratingErrorElement.textContent = 'Network error. Please try again.'
        ratingErrorElement.classList.remove('hidden')
    }
}

function handleRatingSkip() {
    chatRatingElement.classList.add('hidden')
    chatIconElement.classList.remove('hidden')
    clearSession()
}

function connectWebSocket() {
    chatSocket = new WebSocket(`ws://${window.location.host}/ws/${chatUuid}/`)

    chatSocket.onmessage = function(e) {
        console.log('onMessage')

        onChatMessage(JSON.parse(e.data))
    }

    chatSocket.onopen = function(e) {
        console.log('onOpen - chat socket was opened')

        scrollToBottom()
    }

    chatSocket.onclose = function(e) {
        console.log('onClose - chat socket was closed')
    }
}

async function joinChatRoom() {
    console.log('joinChatRoom')

    // Don't create a new room/socket if one is already open
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        console.log('Already connected, reusing existing socket')
        return
    }

    chatName = chatNameElement.value.trim()

    if (!chatName) {
        return
    }
    
    console.log('Join as:', chatName)
    console.log('Room UUID:', chatUuid)

    const data = new FormData()
    data.append('name', chatName)
    data.append('url', chatWindowUrl)

    await fetch(`/api/create_room/${chatUuid}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: data
    })
    .then(function(res){
        return res.json()
    })
    .then(function(data){
        console.log('data', data)
    })

    // Save session to localStorage so it survives page refresh
    saveSession()

    connectWebSocket()
}

async function reconnectChatRoom(session) {
    console.log('Reconnecting to existing room:', session.uuid)

    chatUuid = session.uuid
    chatName = session.name

    // Ensure the room still exists on the backend (get_or_create handles this)
    const data = new FormData()
    data.append('name', chatName)
    data.append('url', chatWindowUrl)

    await fetch(`/api/create_room/${chatUuid}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: data
    })
    .then(function(res){
        return res.json()
    })
    .then(function(data){
        console.log('reconnect data', data)
    })

    // Refresh the session timestamp so the 30-min window resets
    saveSession()

    // Show chat room directly, skip welcome screen    
    chatWelcomeElement.classList.add('hidden') 

    connectWebSocket()
}

/**
 * Event listeners
 */

chatOpenElement.onclick = function(e) {
    e.preventDefault()

    chatIconElement.classList.add('hidden')
    
    // If already connected, go straight back to the chat room
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatRoomElement.classList.remove('hidden')
        scrollToBottom()
    } else {
        chatWelcomeElement.classList.remove('hidden')
    }

    return false
}

chatJoinElement.onclick = function(e) {
    e.preventDefault()

    chatName = chatNameElement.value.trim()

    if (!chatName) {
        return
    }

    chatWelcomeElement.classList.add('hidden')
    chatRoomElement.classList.remove('hidden')

    // Generate a new UUID only for brand new sessions
    if (!chatUuid) {
        chatUuid = Math.random().toString(36).slice(2, 12)
    }

    joinChatRoom()

    return false
}

chatSubmitElement.onclick = function(e) {
    e.preventDefault()

    sendMessage()

    return false
}

chatInputElement.onkeyup = function(e) {
    if (e.keyCode === 13) {
        sendMessage()
    }
}

chatInputElement.onfocus = function(e) {
    chatSocket.send(JSON.stringify({
        'type': 'update',
        'message': 'writing_active',
        'name': chatName,
    }))
}

closeBtn.onclick = function(e) {
    e.preventDefault()

    chatRoomElement.classList.add('hidden')
    chatWelcomeElement.classList.add('hidden')
    chatIconElement.classList.remove('hidden')

    if (document.fullscreenElement) {
        document.exitFullscreen()
    }

    return false
}

fullscreenBtn.onclick = function(e) {
    e.preventDefault()

    if (!document.fullscreenElement) {
        fullscreenBtn.textContent = "※"
        fullscreenBtn.title = "Exit Fullscreen"
        chatElement.requestFullscreen()
    } else if (document.exitFullscreen) {
        fullscreenBtn.textContent = "⛶"
        fullscreenBtn.title = "Fullscreen"
        document.exitFullscreen()
    }
}

ratingSubmitBtn.onclick = function(e) {
    e.preventDefault()
    
    submitRating()
    return false
}

ratingSkipBtn.onclick = function(e) {
    e.preventDefault()

    handleRatingSkip()
    return false
}

/**
 * Auto-reconnect on page load
 */
const existingSession = loadSession()

if (existingSession) {
    reconnectChatRoom(existingSession)
}